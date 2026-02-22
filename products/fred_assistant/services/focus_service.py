"""Focus Mode — Pomodoro-style deep work sessions tied to tasks."""

import uuid
from datetime import datetime, date, timedelta

from products.fred_assistant.database import get_conn, log_activity


def start_focus(task_id: str = None, planned_minutes: int = 25) -> dict:
    session_id = uuid.uuid4().hex[:8]
    now = datetime.now().isoformat()
    task_title = ""
    if task_id:
        with get_conn() as conn:
            row = conn.execute("SELECT title FROM tasks WHERE id=?", (task_id,)).fetchone()
            if row:
                task_title = row["title"]

    with get_conn() as conn:
        conn.execute(
            "INSERT INTO focus_sessions (id, task_id, task_title, started_at, planned_minutes) VALUES (?,?,?,?,?)",
            (session_id, task_id, task_title, now, planned_minutes),
        )
    log_activity("focus_start", "focus_session", session_id, {"task_id": task_id, "minutes": planned_minutes})
    return {
        "id": session_id,
        "task_id": task_id,
        "task_title": task_title,
        "started_at": now,
        "planned_minutes": planned_minutes,
        "completed": False,
    }


def end_focus(session_id: str = None, completed: bool = True, notes: str = "") -> dict | None:
    with get_conn() as conn:
        if not session_id:
            row = conn.execute(
                "SELECT * FROM focus_sessions WHERE ended_at IS NULL ORDER BY started_at DESC LIMIT 1"
            ).fetchone()
            if not row:
                return None
            session_id = row["id"]
        else:
            row = conn.execute("SELECT * FROM focus_sessions WHERE id=?", (session_id,)).fetchone()
            if not row:
                return None

        now = datetime.now().isoformat()
        conn.execute(
            "UPDATE focus_sessions SET ended_at=?, completed=?, notes=? WHERE id=?",
            (now, 1 if completed else 0, notes, session_id),
        )
    log_activity("focus_end", "focus_session", session_id, {"completed": completed})
    result = dict(row)
    result["ended_at"] = now
    result["completed"] = completed
    result["notes"] = notes
    return result


def get_active_session() -> dict | None:
    with get_conn() as conn:
        row = conn.execute(
            "SELECT * FROM focus_sessions WHERE ended_at IS NULL ORDER BY started_at DESC LIMIT 1"
        ).fetchone()
        if row:
            return dict(row)
    return None


def get_focus_stats(days: int = 7) -> dict:
    cutoff = (date.today() - timedelta(days=days)).isoformat()
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM focus_sessions WHERE started_at >= ? AND ended_at IS NOT NULL",
            (cutoff,),
        ).fetchall()

    sessions = [dict(r) for r in rows]
    total_minutes = 0
    for s in sessions:
        try:
            start = datetime.fromisoformat(s["started_at"])
            end = datetime.fromisoformat(s["ended_at"])
            total_minutes += (end - start).total_seconds() / 60
        except (ValueError, TypeError):
            total_minutes += s.get("planned_minutes", 25)

    completed = [s for s in sessions if s.get("completed")]
    return {
        "total_minutes": round(total_minutes),
        "total_sessions": len(sessions),
        "completed_sessions": len(completed),
        "avg_duration": round(total_minutes / len(sessions)) if sessions else 0,
        "days": days,
    }


def list_sessions(days: int = 7) -> list[dict]:
    cutoff = (date.today() - timedelta(days=days)).isoformat()
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM focus_sessions WHERE started_at >= ? ORDER BY started_at DESC",
            (cutoff,),
        ).fetchall()
    return [dict(r) for r in rows]
