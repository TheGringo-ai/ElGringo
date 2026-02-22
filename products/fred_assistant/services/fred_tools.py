"""
Fred Tools — Action execution engine for Fred Assistant.
Parses ACTION: markers from AI responses and executes them against local services.
"""

import json
import logging
import os
import re
import subprocess
import uuid
from datetime import date, datetime, timedelta
from pathlib import Path

from products.fred_assistant.database import get_conn, log_activity
from products.fred_assistant.services import (
    calendar_service,
    coach_service,
    content_service,
    crm_service,
    focus_service,
    inbox_service,
    memory_service,
    metrics_service,
    playbook_service,
    projects_service,
    publish_service,
    task_service,
)

logger = logging.getLogger(__name__)

# ── Security ────────────────────────────────────────────────────────

ALLOWED_ROOTS = [
    os.path.expanduser("~/Development"),
    os.path.expanduser("~/Documents"),
    "/tmp",
    "/private/tmp",  # macOS resolves /tmp -> /private/tmp
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
    task = task_service.create_task(data)
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
    task = task_service.update_task(task_id, updates)
    if not task:
        return {"success": False, "error": f"Task {task_id} not found"}
    return {"success": True, "task": task, "message": f"Updated task: {task['title']}"}


def _exec_complete_task(params: dict) -> dict:
    task_id = params.get("task_id")
    if not task_id:
        return {"success": False, "error": "task_id is required"}
    task = task_service.update_task(task_id, {"status": "done"})
    if not task:
        return {"success": False, "error": f"Task {task_id} not found"}
    return {"success": True, "task": task, "message": f"Completed: {task['title']}"}


def _exec_delete_task(params: dict) -> dict:
    task_id = params.get("task_id")
    if not task_id:
        return {"success": False, "error": "task_id is required"}
    task = task_service.get_task(task_id)
    if not task:
        return {"success": False, "error": f"Task {task_id} not found"}
    title = task["title"]
    task_service.delete_task(task_id)
    return {"success": True, "message": f"Deleted task: {title}"}


def _exec_list_tasks(params: dict) -> dict:
    board = params.get("board")
    status = params.get("status")
    tasks = task_service.list_tasks(board_id=board, status=status)
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
        task = task_service.create_task({
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
    mem = memory_service.remember(category, key, value)
    return {"success": True, "memory": mem, "message": f"Remembered: {key} = {value}"}


def _exec_search_memory(params: dict) -> dict:
    query = params.get("query", "")
    if not query:
        return {"success": False, "error": "query is required"}
    results = memory_service.search_memories(query)
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
        results = memory_service.search_memories(key)
        if category:
            results = [m for m in results if m["category"] == category]
        if not results:
            return {"success": False, "error": f"No memory found for key '{key}'"}
        memory_id = results[0]["id"]
    mem = memory_service.get_memory(memory_id)
    if not mem:
        return {"success": False, "error": f"Memory {memory_id} not found"}
    label = f"{mem['key']}: {mem['value']}"
    memory_service.forget(memory_id)
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
    event = calendar_service.create_event(data)
    return {"success": True, "event": event, "message": f"Created event: {event['title']} on {data['start_date']}"}


def _exec_list_events(params: dict) -> dict:
    days = params.get("days", 7)
    events = calendar_service.get_upcoming(days=days)
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
    event = calendar_service.update_event(event_id, updates)
    if not event:
        return {"success": False, "error": f"Event {event_id} not found"}
    return {"success": True, "event": event, "message": f"Updated event: {event['title']}"}


def _exec_delete_event(params: dict) -> dict:
    event_id = params.get("event_id")
    if not event_id:
        return {"success": False, "error": "event_id is required"}
    event = calendar_service.get_event(event_id)
    if not event:
        return {"success": False, "error": f"Event {event_id} not found"}
    title = event["title"]
    calendar_service.delete_event(event_id)
    return {"success": True, "message": f"Deleted event: {title}"}


# ─── Goals & Accountability ───────────────────────────────────────

def _exec_create_goal(params: dict) -> dict:
    data = {
        "title": params.get("title", "Untitled goal"),
        "category": params.get("category", "business"),
        "target_date": params.get("target_date"),
        "description": params.get("description", ""),
    }
    goal = coach_service.create_goal(data)
    return {"success": True, "goal": goal, "message": f"Created goal: {goal['title']}"}


def _exec_update_goal(params: dict) -> dict:
    goal_id = params.get("goal_id")
    if not goal_id:
        return {"success": False, "error": "goal_id is required"}
    updates = {}
    for key in ["progress", "status", "title", "description"]:
        if key in params:
            updates[key] = params[key]
    goal = coach_service.update_goal(goal_id, updates)
    if not goal:
        return {"success": False, "error": f"Goal {goal_id} not found"}
    return {"success": True, "goal": goal, "message": f"Updated goal: {goal['title']} ({goal['progress']}%)"}


def _exec_delete_goal(params: dict) -> dict:
    goal_id = params.get("goal_id")
    if not goal_id:
        return {"success": False, "error": "goal_id is required"}
    goal = coach_service.get_goal(goal_id)
    if not goal:
        return {"success": False, "error": f"Goal {goal_id} not found"}
    title = goal["title"]
    coach_service.delete_goal(goal_id)
    return {"success": True, "message": f"Deleted goal: {title}"}


def _exec_accountability_check(params: dict) -> dict:
    goals = coach_service.list_goals(status="active")
    stats = task_service.get_dashboard_stats()
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
    projects = projects_service.list_projects()
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
    review = await coach_service.generate_weekly_review()
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
    projects_dir = os.path.expanduser("~/Development/Projects")
    path = os.path.join(projects_dir, name)
    if not os.path.isdir(path):
        return {"success": False, "error": f"Project '{name}' not found"}

    info = projects_service.get_project_info(path)
    commits = projects_service.get_recent_commits(path, count=5)
    branches = projects_service.get_branches(path)

    return {
        "success": True,
        "project": info,
        "recent_commits": commits,
        "branches": [b["name"] for b in branches],
        "message": f"Project review: {name} ({', '.join(info.get('tech_stack', []))})",
    }


def _exec_list_projects(params: dict) -> dict:
    projects = projects_service.list_projects()
    summary = []
    for p in projects[:20]:
        line = f"{p['name']} ({', '.join(p.get('tech_stack', [])[:3])})"
        if p.get("git_status") == "dirty":
            line += " [uncommitted changes]"
        summary.append(line)
    return {"success": True, "count": len(projects), "projects": summary}


def _exec_git_status(params: dict) -> dict:
    name = params.get("project")
    if not name:
        return {"success": False, "error": "project name is required"}
    projects_dir = os.path.expanduser("~/Development/Projects")
    path = os.path.join(projects_dir, name)
    if not os.path.isdir(path):
        return {"success": False, "error": f"Project '{name}' not found"}

    info = projects_service.get_project_info(path)
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
    projects_dir = os.path.expanduser("~/Development/Projects")
    path = os.path.join(projects_dir, name)
    if not os.path.isdir(path):
        return {"success": False, "error": f"Project '{name}' not found"}

    commits = projects_service.get_recent_commits(path, count=count)
    summary = [f"[{c['hash']}] {c['message']} ({c['date']})" for c in commits]
    return {"success": True, "commits": summary, "count": len(commits)}


def _exec_git_diff(params: dict) -> dict:
    name = params.get("project")
    if not name:
        return {"success": False, "error": "project name is required"}
    projects_dir = os.path.expanduser("~/Development/Projects")
    path = os.path.join(projects_dir, name)
    if not os.path.isdir(path):
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
    path = params.get("path", "~/Development/Projects")
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
    path = params.get("path", "~/Development/Projects")
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
            "matches": [l for l in lines if l],
            "count": len([l for l in lines if l]),
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

    result = await content_service.generate_content(
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
    result = content_service.update_content(content_id, updates)
    if not result:
        return {"success": False, "error": f"Content {content_id} not found"}
    return {"success": True, "content": result, "message": f"Scheduled '{result['title']}' for {scheduled_date}"}


# ─── Focus Mode ───────────────────────────────────────────────────

def _exec_start_focus(params: dict) -> dict:
    task_id = params.get("task_id")
    minutes = params.get("minutes", 25)
    session = focus_service.start_focus(task_id=task_id, planned_minutes=minutes)
    return {"success": True, "session": session, "message": f"Focus session started ({minutes} min){' on: ' + session.get('task_title') if session.get('task_title') else ''}"}


def _exec_end_focus(params: dict) -> dict:
    notes = params.get("notes", "")
    session = focus_service.end_focus(notes=notes)
    if not session:
        return {"success": False, "error": "No active focus session"}
    return {"success": True, "session": session, "message": "Focus session ended"}


def _exec_focus_stats(params: dict) -> dict:
    days = params.get("days", 7)
    stats = focus_service.get_focus_stats(days)
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
    lead = crm_service.create_lead(data)
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
    lead = crm_service.update_lead(lead_id, updates)
    if not lead:
        return {"success": False, "error": f"Lead {lead_id} not found"}
    return {"success": True, "lead": lead, "message": f"Updated lead: {lead['name']} ({lead['pipeline_stage']})"}


def _exec_log_outreach(params: dict) -> dict:
    lead_id = params.get("lead_id")
    if not lead_id:
        return {"success": False, "error": "lead_id is required"}
    entry = crm_service.log_outreach(
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
    lead = crm_service.schedule_followup(lead_id, followup_date, params.get("notes", ""))
    if not lead:
        return {"success": False, "error": f"Lead {lead_id} not found"}
    return {"success": True, "lead": lead, "message": f"Followup scheduled for {followup_date} with {lead['name']}"}


def _exec_list_leads(params: dict) -> dict:
    stage = params.get("stage")
    leads = crm_service.list_leads(stage=stage)
    summary = [f"[{l['id']}] {l['name']} ({l['company'] or 'no co.'}) — {l['pipeline_stage']}, ${l['deal_value']:,.0f}" for l in leads[:20]]
    return {"success": True, "count": len(leads), "leads": summary, "message": f"Found {len(leads)} leads" + (f" in {stage}" if stage else "")}


def _exec_pipeline_summary(params: dict) -> dict:
    summary = crm_service.get_pipeline_summary()
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
    result = publish_service.approve_content(content_id)
    if not result:
        return {"success": False, "error": f"Content {content_id} not found"}
    return {"success": True, "content": result, "message": f"Approved: {result.get('title', content_id)}"}


def _exec_publish_content(params: dict) -> dict:
    content_id = params.get("content_id")
    if not content_id:
        return {"success": False, "error": "content_id is required"}
    platform = params.get("platform")
    dry_run = params.get("dry_run", True)
    result = publish_service.publish_content(content_id, platform, dry_run)
    if not result:
        return {"success": False, "error": f"Content {content_id} not found"}
    return {"success": True, "result": result, "message": result.get("message", "Published")}


# ─── Metrics / CEO Lens ──────────────────────────────────────────

def _exec_ceo_lens(params: dict) -> dict:
    metrics = metrics_service.get_current_metrics()
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
    result = metrics_service.log_metric(name, float(value))
    return {"success": True, "snapshot": result, "message": f"Logged {name} = {value}"}


# ─── Inbox ────────────────────────────────────────────────────────

def _exec_inbox(params: dict) -> dict:
    items = inbox_service.get_inbox()
    summary = [f"[{i['type']}] {i['title']} — {i['description']}" for i in items[:15]]
    return {"success": True, "count": len(items), "items": summary, "message": f"Inbox: {len(items)} items needing attention"}


def _exec_inbox_summary(params: dict) -> dict:
    counts = inbox_service.get_inbox_count()
    lines = [f"{t}: {c}" for t, c in counts.get("by_type", {}).items()]
    return {"success": True, "counts": counts, "message": f"Inbox summary: {counts['total']} total\n" + "\n".join(lines)}


# ─── Playbooks ────────────────────────────────────────────────────

async def _exec_run_playbook(params: dict) -> dict:
    name = params.get("name")
    if not name:
        return {"success": False, "error": "playbook name is required"}
    pb = playbook_service.get_playbook_by_name(name)
    if not pb:
        return {"success": False, "error": f"Playbook '{name}' not found"}
    result = await playbook_service.run_playbook(pb["id"])
    return {
        "success": True,
        "result": result,
        "message": f"Ran playbook '{name}': {result['status']} ({len(result.get('steps', []))} steps)",
    }


def _exec_list_playbooks(params: dict) -> dict:
    category = params.get("category")
    playbooks = playbook_service.list_playbooks(category)
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
    pb = playbook_service.create_playbook(data)
    return {"success": True, "playbook": pb, "message": f"Created playbook: {pb['name']}"}


async def _exec_run_autopilot(params: dict) -> dict:
    name = params.get("name")
    if not name:
        return {"success": False, "error": "autopilot name is required"}
    pb = playbook_service.get_playbook_by_name(name)
    if not pb:
        return {"success": False, "error": f"Autopilot '{name}' not found"}
    if pb.get("category") != "autopilot":
        return {"success": False, "error": f"'{name}' is not an autopilot playbook (category: {pb.get('category')})"}
    result = await playbook_service.run_playbook(pb["id"])
    return {
        "success": True,
        "result": result,
        "message": f"Ran autopilot '{name}': {result['status']}",
    }


def _exec_list_autopilots(params: dict) -> dict:
    playbooks = playbook_service.list_playbooks("autopilot")
    summary = [f"{p['name']} — {p['description']}" for p in playbooks]
    return {"success": True, "count": len(playbooks), "autopilots": summary}


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
                   "params": "path (default: ~/Development/Projects), pattern (glob filter)"},
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
