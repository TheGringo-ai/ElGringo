"""CEO Lens Metrics — Live aggregation + snapshot history for founder dashboard."""

import json
import uuid
from datetime import date, datetime, timedelta

from products.fred_assistant.database import get_conn, log_activity


def get_current_metrics() -> dict:
    """Live-aggregated metrics from all tables."""
    today = date.today().isoformat()
    week_start = (date.today() - timedelta(days=date.today().weekday())).isoformat()

    with get_conn() as conn:
        # MRR from latest snapshot
        mrr_row = conn.execute(
            "SELECT mrr FROM metrics_snapshots ORDER BY date DESC LIMIT 1"
        ).fetchone()
        mrr = mrr_row["mrr"] if mrr_row else 0

        # Outreach this week
        leads_contacted = conn.execute(
            "SELECT COUNT(DISTINCT lead_id) as c FROM outreach_log WHERE created_at >= ?", (week_start,)
        ).fetchone()["c"]

        # Pipeline stages this week
        calls_booked = conn.execute(
            "SELECT COUNT(*) as c FROM leads WHERE pipeline_stage='call_booked' AND updated_at >= ?", (week_start,)
        ).fetchone()["c"]

        trials_started = conn.execute(
            "SELECT COUNT(*) as c FROM leads WHERE pipeline_stage='trial' AND updated_at >= ?", (week_start,)
        ).fetchone()["c"]

        deals_closed = conn.execute(
            "SELECT COUNT(*) as c FROM leads WHERE pipeline_stage='paid' AND updated_at >= ?", (week_start,)
        ).fetchone()["c"]

        # Sprint completion
        total_tasks = conn.execute(
            "SELECT COUNT(*) as c FROM tasks WHERE status != 'done'"
        ).fetchone()["c"]
        completed_tasks = conn.execute(
            "SELECT COUNT(*) as c FROM tasks WHERE status = 'done' AND completed_at >= ?", (week_start,)
        ).fetchone()["c"]
        all_active = total_tasks + completed_tasks
        sprint_pct = round((completed_tasks / all_active) * 100, 1) if all_active > 0 else 0

        # Content published this week
        content_published = conn.execute(
            "SELECT COUNT(*) as c FROM content_items WHERE status='published' AND updated_at >= ?", (week_start,)
        ).fetchone()["c"]

        # Overdue tasks
        overdue = conn.execute(
            "SELECT COUNT(*) as c FROM tasks WHERE due_date < ? AND status != 'done'", (today,)
        ).fetchone()["c"]

        # Focus minutes today
        focus_rows = conn.execute(
            "SELECT started_at, ended_at FROM focus_sessions WHERE started_at >= ? AND ended_at IS NOT NULL",
            (today,),
        ).fetchall()

    focus_minutes = 0
    for r in focus_rows:
        try:
            start = datetime.fromisoformat(r["started_at"])
            end = datetime.fromisoformat(r["ended_at"])
            focus_minutes += (end - start).total_seconds() / 60
        except (ValueError, TypeError):
            pass

    return {
        "mrr": mrr,
        "leads_contacted": leads_contacted,
        "calls_booked": calls_booked,
        "trials_started": trials_started,
        "deals_closed": deals_closed,
        "sprint_completion_pct": sprint_pct,
        "content_published": content_published,
        "overdue_tasks": overdue,
        "focus_minutes_today": round(focus_minutes),
    }


def save_snapshot(data: dict = None) -> dict:
    """Save today's metrics as a snapshot."""
    snapshot_id = uuid.uuid4().hex[:8]
    today = date.today().isoformat()
    metrics = data or get_current_metrics()
    custom = json.dumps(metrics.get("custom_metrics", {}))

    with get_conn() as conn:
        conn.execute(
            """INSERT OR REPLACE INTO metrics_snapshots
               (id, date, mrr, leads_contacted, calls_booked, trials_started, deals_closed,
                sprint_completion_pct, content_published, revenue, custom_metrics)
               VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
            (
                snapshot_id,
                today,
                metrics.get("mrr", 0),
                metrics.get("leads_contacted", 0),
                metrics.get("calls_booked", 0),
                metrics.get("trials_started", 0),
                metrics.get("deals_closed", 0),
                metrics.get("sprint_completion_pct", 0),
                metrics.get("content_published", 0),
                metrics.get("revenue", 0),
                custom,
            ),
        )
    log_activity("metrics_snapshot", "metrics", snapshot_id)
    return get_snapshot(today)


def get_snapshot(snapshot_date: str) -> dict | None:
    with get_conn() as conn:
        row = conn.execute("SELECT * FROM metrics_snapshots WHERE date=?", (snapshot_date,)).fetchone()
        if not row:
            return None
        d = dict(row)
        try:
            d["custom_metrics"] = json.loads(d.get("custom_metrics") or "{}")
        except (json.JSONDecodeError, TypeError):
            d["custom_metrics"] = {}
        return d


def get_snapshots(days: int = 30) -> list[dict]:
    cutoff = (date.today() - timedelta(days=days)).isoformat()
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM metrics_snapshots WHERE date >= ? ORDER BY date DESC", (cutoff,)
        ).fetchall()
    results = []
    for r in rows:
        d = dict(r)
        try:
            d["custom_metrics"] = json.loads(d.get("custom_metrics") or "{}")
        except (json.JSONDecodeError, TypeError):
            d["custom_metrics"] = {}
        results.append(d)
    return results


def log_metric(name: str, value: float) -> dict:
    """Log a custom metric (e.g., MRR). Upserts today's snapshot."""
    today = date.today().isoformat()
    snapshot = get_snapshot(today)

    if name == "mrr":
        if snapshot:
            with get_conn() as conn:
                conn.execute("UPDATE metrics_snapshots SET mrr=? WHERE date=?", (value, today))
            return get_snapshot(today)
        else:
            return save_snapshot({"mrr": value})

    if name == "revenue":
        if snapshot:
            with get_conn() as conn:
                conn.execute("UPDATE metrics_snapshots SET revenue=? WHERE date=?", (value, today))
            return get_snapshot(today)
        else:
            return save_snapshot({"revenue": value})

    # Custom metric — store in custom_metrics JSON
    custom = snapshot["custom_metrics"] if snapshot else {}
    custom[name] = value
    if snapshot:
        with get_conn() as conn:
            conn.execute(
                "UPDATE metrics_snapshots SET custom_metrics=? WHERE date=?",
                (json.dumps(custom), today),
            )
        return get_snapshot(today)
    else:
        return save_snapshot({"custom_metrics": custom})
