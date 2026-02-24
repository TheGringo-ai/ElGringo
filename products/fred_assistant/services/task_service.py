"""Task and board management service."""

import json
import logging
import uuid
from datetime import datetime, date

from products.fred_assistant.database import get_conn, log_activity

logger = logging.getLogger(__name__)

TASK_REVIEW_SYSTEM = """You are Fred, an AI development assistant. A developer is reviewing a task and wants your advice.

Task: {title}
Priority: {priority}/5
Status: {status}
Board: {board_id}
Description: {description}
Notes: {notes}
{project_context}

Give the developer practical, actionable advice in plain English:
1. WHY this task matters and its impact
2. HOW to approach it (specific steps, tools, patterns)
3. WHAT to watch out for (risks, gotchas, dependencies)
4. ESTIMATED complexity (small/medium/large)

Be concise, specific, and reference actual files/patterns when possible.
Do NOT output TASK: blocks — this is advice only."""


def _row_to_task(row) -> dict:
    d = dict(row)
    raw_tags = d.get("tags") or "[]"
    try:
        parsed = json.loads(raw_tags)
        # Handle double-encoded JSON strings
        if isinstance(parsed, str):
            parsed = json.loads(parsed)
        d["tags"] = parsed if isinstance(parsed, list) else []
    except (json.JSONDecodeError, TypeError):
        d["tags"] = []
    return d


def _row_to_board(row) -> dict:
    d = dict(row)
    d["columns"] = json.loads(d.get("columns") or "[]")
    return d


# ── Boards ────────────────────────────────────────────────────────

def list_boards(include_archived=False):
    with get_conn() as conn:
        q = "SELECT * FROM boards" if include_archived else "SELECT * FROM boards WHERE archived=0"
        rows = conn.execute(f"{q} ORDER BY position").fetchall()
        boards = []
        for r in rows:
            b = _row_to_board(r)
            count = conn.execute(
                "SELECT COUNT(*) FROM tasks WHERE board_id=? AND status!='done'", (b["id"],)
            ).fetchone()[0]
            b["task_count"] = count
            boards.append(b)
        return boards


def get_board(board_id: str):
    with get_conn() as conn:
        row = conn.execute("SELECT * FROM boards WHERE id=?", (board_id,)).fetchone()
        if not row:
            return None
        b = _row_to_board(row)
        count = conn.execute(
            "SELECT COUNT(*) FROM tasks WHERE board_id=? AND status!='done'", (board_id,)
        ).fetchone()[0]
        b["task_count"] = count
        return b


def create_board(name: str, icon: str = "📋", color: str = "blue", columns: list = None):
    board_id = name.lower().replace(" ", "_")[:20]
    cols = json.dumps(columns or ["todo", "in_progress", "done"])
    with get_conn() as conn:
        pos = conn.execute("SELECT COALESCE(MAX(position),0)+1 FROM boards").fetchone()[0]
        conn.execute(
            "INSERT INTO boards (id, name, icon, color, position, columns) VALUES (?,?,?,?,?,?)",
            (board_id, name, icon, color, pos, cols),
        )
    log_activity("board_created", "board", board_id)
    return get_board(board_id)


# ── Tasks ─────────────────────────────────────────────────────────

def list_tasks(board_id: str = None, status: str = None, due_date: str = None):
    with get_conn() as conn:
        q = "SELECT * FROM tasks WHERE 1=1"
        params = []
        if board_id:
            q += " AND board_id=?"
            params.append(board_id)
        if status:
            q += " AND status=?"
            params.append(status)
        if due_date:
            q += " AND due_date=?"
            params.append(due_date)
        q += " ORDER BY priority ASC, position ASC, created_at DESC"
        return [_row_to_task(r) for r in conn.execute(q, params).fetchall()]


def get_task(task_id: str):
    with get_conn() as conn:
        row = conn.execute("SELECT * FROM tasks WHERE id=?", (task_id,)).fetchone()
        return _row_to_task(row) if row else None


def create_task(data: dict) -> dict:
    task_id = uuid.uuid4().hex[:8]
    now = datetime.utcnow().isoformat()
    with get_conn() as conn:
        pos = conn.execute(
            "SELECT COALESCE(MAX(position),0)+1 FROM tasks WHERE board_id=? AND status=?",
            (data.get("board_id", "work"), data.get("status", "todo")),
        ).fetchone()[0]
        conn.execute(
            """INSERT INTO tasks (id, board_id, title, description, status, priority,
               category, due_date, due_time, recurring, tags, notes, position, created_at, updated_at)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (
                task_id,
                data.get("board_id", "work"),
                data["title"],
                data.get("description", ""),
                data.get("status", "todo"),
                data.get("priority", 3),
                data.get("category", "general"),
                data.get("due_date"),
                data.get("due_time"),
                data.get("recurring"),
                json.dumps(data.get("tags", [])),
                data.get("notes", ""),
                pos,
                now,
                now,
            ),
        )
    log_activity("task_created", "task", task_id, {"title": data["title"]})
    task = get_task(task_id)
    # Index in RAG (fire-and-forget)
    try:
        from products.fred_assistant.services.rag_service import get_rag
        get_rag().index_task(task)
    except Exception:
        pass
    return task


def update_task(task_id: str, data: dict) -> dict:
    now = datetime.utcnow().isoformat()
    sets = []
    params = []
    for field in ["title", "description", "status", "priority", "category",
                   "due_date", "due_time", "notes", "board_id", "position"]:
        if field in data and data[field] is not None:
            sets.append(f"{field}=?")
            params.append(data[field])
    if "tags" in data and data["tags"] is not None:
        sets.append("tags=?")
        params.append(json.dumps(data["tags"]))
    if "status" in data and data["status"] == "done":
        sets.append("completed_at=?")
        params.append(now)
    sets.append("updated_at=?")
    params.append(now)
    params.append(task_id)

    with get_conn() as conn:
        conn.execute(f"UPDATE tasks SET {','.join(sets)} WHERE id=?", params)
    log_activity("task_updated", "task", task_id, data)
    task = get_task(task_id)
    # Index in RAG: index if active, delete if done (fire-and-forget)
    try:
        from products.fred_assistant.services.rag_service import get_rag
        get_rag().index_task(task)
    except Exception:
        pass
    return task


def delete_task(task_id: str):
    with get_conn() as conn:
        conn.execute("DELETE FROM tasks WHERE id=?", (task_id,))
    log_activity("task_deleted", "task", task_id)
    # Remove from RAG (fire-and-forget)
    try:
        from products.fred_assistant.services.rag_service import get_rag
        get_rag().delete_task(task_id)
    except Exception:
        pass


def get_today_tasks():
    today = date.today().isoformat()
    with get_conn() as conn:
        rows = conn.execute(
            """SELECT * FROM tasks WHERE
               (due_date=? OR status='in_progress' OR (due_date<? AND status!='done'))
               ORDER BY priority ASC, due_date ASC""",
            (today, today),
        ).fetchall()
        return [_row_to_task(r) for r in rows]


def get_dashboard_stats() -> dict:
    today = date.today().isoformat()
    with get_conn() as conn:
        total = conn.execute("SELECT COUNT(*) FROM tasks WHERE status!='done'").fetchone()[0]
        completed_today = conn.execute(
            "SELECT COUNT(*) FROM tasks WHERE completed_at LIKE ?", (f"{today}%",)
        ).fetchone()[0]
        overdue = conn.execute(
            "SELECT COUNT(*) FROM tasks WHERE due_date<? AND status!='done'", (today,)
        ).fetchone()[0]
        in_progress = conn.execute(
            "SELECT COUNT(*) FROM tasks WHERE status='in_progress'"
        ).fetchone()[0]
        due_today = conn.execute(
            "SELECT COUNT(*) FROM tasks WHERE due_date=? AND status!='done'", (today,)
        ).fetchone()[0]
        boards = conn.execute("SELECT COUNT(*) FROM boards WHERE archived=0").fetchone()[0]
        memories = conn.execute("SELECT COUNT(*) FROM memories").fetchone()[0]

        # Streak: consecutive days with at least 1 completion
        streak = 0
        d = date.today()
        from datetime import timedelta
        while True:
            count = conn.execute(
                "SELECT COUNT(*) FROM tasks WHERE completed_at LIKE ?",
                (f"{d.isoformat()}%",),
            ).fetchone()[0]
            if count > 0:
                streak += 1
                d -= timedelta(days=1)
            else:
                break

        return {
            "total_tasks": total,
            "completed_today": completed_today,
            "overdue": overdue,
            "in_progress": in_progress,
            "due_today": due_today,
            "boards": boards,
            "memories": memories,
            "streak_days": streak,
        }


async def stream_task_review(task_id: str):
    """Stream AI review/advice for a specific task. Yields {type, data} dicts."""
    from products.fred_assistant.services.llm_shared import get_gemini, llm_response

    task = get_task(task_id)
    if not task:
        yield {"type": "error", "data": "Task not found"}
        return

    # Build project context if task has a project tag
    project_context = ""
    project_tags = [t.replace("project:", "") for t in (task.get("tags") or []) if t.startswith("project:")]
    if project_tags:
        try:
            from products.fred_assistant.services.projects_service import get_project
            proj = get_project(project_tags[0])
            if proj:
                project_context = (
                    f"Project: {project_tags[0]}\n"
                    f"Tech stack: {', '.join(proj.get('tech_stack', []))}\n"
                    f"Branch: {proj.get('git_branch', 'N/A')}\n"
                    f"Last commit: {proj.get('last_commit_msg', 'N/A')}"
                )
        except Exception:
            project_context = f"Project: {project_tags[0]}"

    system = TASK_REVIEW_SYSTEM.format(
        title=task.get("title", ""),
        priority=task.get("priority", 3),
        status=task.get("status", "todo"),
        board_id=task.get("board_id", "work"),
        description=task.get("description", "") or "(none)",
        notes=task.get("notes", "") or "(none)",
        project_context=project_context,
    )

    prompt = f"Please review this task and give me your advice: {task['title']}"
    full_response = ""
    streamed = False

    # Try streaming via Gemini first
    agent = get_gemini()
    if agent and hasattr(agent, "stream_response"):
        try:
            async for chunk in agent.stream_response(prompt, system_override=system):
                if hasattr(chunk, "content") and chunk.content:
                    full_response += chunk.content
                    yield {"type": "token", "data": chunk.content}
                    streamed = True
                elif isinstance(chunk, str):
                    full_response += chunk
                    yield {"type": "token", "data": chunk}
                    streamed = True
        except Exception as e:
            logger.warning("Task review stream failed: %s — falling back", e)

    # Fallback to llm_response
    if not streamed or not full_response.strip():
        try:
            content = await llm_response(prompt, system, feature="task_review")
            if content:
                chunk_size = 20
                for i in range(0, len(content), chunk_size):
                    yield {"type": "token", "data": content[i:i + chunk_size]}
            else:
                yield {"type": "token", "data": "AI service is temporarily unavailable. Please try again."}
        except Exception as e:
            logger.warning("Task review fallback failed: %s", e)
            yield {"type": "token", "data": f"Error: {e}"}

    yield {"type": "done", "data": ""}
