"""
Calendar Service — events, time blocking, deadlines.
"""

import json
import uuid
from datetime import date, datetime, timedelta

from products.fred_assistant.database import get_conn, log_activity


def list_events(start_date: str = None, end_date: str = None, event_type: str = None) -> list[dict]:
    """List calendar events, optionally filtered by date range or type."""
    with get_conn() as conn:
        query = "SELECT * FROM calendar_events WHERE 1=1"
        params = []

        if start_date:
            query += " AND start_date >= ?"
            params.append(start_date)
        if end_date:
            query += " AND start_date <= ?"
            params.append(end_date)
        if event_type:
            query += " AND event_type = ?"
            params.append(event_type)

        query += " ORDER BY start_date, start_time"
        rows = conn.execute(query, params).fetchall()
        return [dict(r) for r in rows]


def get_event(event_id: str) -> dict | None:
    with get_conn() as conn:
        row = conn.execute("SELECT * FROM calendar_events WHERE id=?", (event_id,)).fetchone()
        return dict(row) if row else None


def create_event(data: dict) -> dict:
    event_id = uuid.uuid4().hex[:8]
    now = datetime.now().isoformat()

    with get_conn() as conn:
        conn.execute(
            """INSERT INTO calendar_events
               (id, title, description, event_type, start_date, start_time, end_date, end_time,
                all_day, recurring, color, location, linked_task_id, created_at, updated_at)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (
                event_id, data["title"], data.get("description", ""),
                data.get("event_type", "event"), data["start_date"],
                data.get("start_time"), data.get("end_date"),
                data.get("end_time"), 1 if data.get("all_day") else 0,
                data.get("recurring"), data.get("color", "blue"),
                data.get("location", ""), data.get("linked_task_id"),
                now, now,
            ),
        )

    log_activity("create_event", "calendar_event", event_id, {"title": data["title"]})
    return get_event(event_id)


def update_event(event_id: str, data: dict) -> dict | None:
    existing = get_event(event_id)
    if not existing:
        return None

    fields = []
    values = []
    for key in ["title", "description", "event_type", "start_date", "start_time",
                "end_date", "end_time", "all_day", "recurring", "color", "location"]:
        if key in data and data[key] is not None:
            if key == "all_day":
                fields.append(f"{key}=?")
                values.append(1 if data[key] else 0)
            else:
                fields.append(f"{key}=?")
                values.append(data[key])

    if fields:
        fields.append("updated_at=?")
        values.append(datetime.now().isoformat())
        values.append(event_id)
        with get_conn() as conn:
            conn.execute(f"UPDATE calendar_events SET {','.join(fields)} WHERE id=?", values)

    return get_event(event_id)


def delete_event(event_id: str):
    with get_conn() as conn:
        conn.execute("DELETE FROM calendar_events WHERE id=?", (event_id,))
    log_activity("delete_event", "calendar_event", event_id)


def get_today_events() -> list[dict]:
    today = date.today().isoformat()
    return list_events(start_date=today, end_date=today)


def get_week_events() -> list[dict]:
    today = date.today()
    start = today - timedelta(days=today.weekday())  # Monday
    end = start + timedelta(days=6)  # Sunday
    return list_events(start_date=start.isoformat(), end_date=end.isoformat())


def get_upcoming(days: int = 7) -> list[dict]:
    today = date.today()
    end = today + timedelta(days=days)
    return list_events(start_date=today.isoformat(), end_date=end.isoformat())
