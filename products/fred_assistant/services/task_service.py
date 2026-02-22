"""Task and board management service."""

import json
import uuid
from datetime import datetime, date

from products.fred_assistant.database import get_conn, log_activity


def _row_to_task(row) -> dict:
    d = dict(row)
    d["tags"] = json.loads(d.get("tags") or "[]")
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
    return get_task(task_id)


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
    return get_task(task_id)


def delete_task(task_id: str):
    with get_conn() as conn:
        conn.execute("DELETE FROM tasks WHERE id=?", (task_id,))
    log_activity("task_deleted", "task", task_id)


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
