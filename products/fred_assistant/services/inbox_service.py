"""Unified Inbox — Aggregated, prioritized feed of action-needed items."""

from datetime import date, timedelta

from products.fred_assistant.database import get_conn


def get_inbox() -> list[dict]:
    """Aggregate action-needed items from all tables, sorted by priority."""
    items = []
    today = date.today().isoformat()
    three_days = (date.today() + timedelta(days=3)).isoformat()
    fourteen_days_ago = (date.today() - timedelta(days=14)).isoformat()

    with get_conn() as conn:
        # 1. Overdue tasks (highest priority)
        overdue_rows = conn.execute(
            "SELECT id, title, due_date, board_id FROM tasks WHERE due_date < ? AND status != 'done' ORDER BY due_date LIMIT 20",
            (today,),
        ).fetchall()
        for r in overdue_rows:
            items.append({
                "type": "overdue_task",
                "title": r["title"],
                "description": f"Due {r['due_date']} on {r['board_id']} board",
                "priority": 1,
                "entity_id": r["id"],
                "action_hint": "complete_task",
            })

        # 2. Content pending approval
        try:
            pending_rows = conn.execute(
                "SELECT id, title, platform FROM content_items WHERE approval_status = 'pending' AND status = 'draft' ORDER BY created_at DESC LIMIT 10",
            ).fetchall()
            for r in pending_rows:
                items.append({
                    "type": "pending_approval",
                    "title": r["title"],
                    "description": f"{r['platform']} content awaiting approval",
                    "priority": 2,
                    "entity_id": r["id"],
                    "action_hint": "approve_content",
                })
        except Exception:
            pass  # approval_status column might not exist yet

        # 3. Leads needing followup
        followup_rows = conn.execute(
            "SELECT id, name, company, next_followup, pipeline_stage FROM leads WHERE next_followup IS NOT NULL AND next_followup <= ? AND pipeline_stage NOT IN ('paid', 'churned') ORDER BY next_followup LIMIT 15",
            (three_days,),
        ).fetchall()
        for r in followup_rows:
            items.append({
                "type": "followup_due",
                "title": f"Follow up with {r['name']}",
                "description": f"{r['company'] or 'No company'} — {r['pipeline_stage']} stage, followup due {r['next_followup']}",
                "priority": 2,
                "entity_id": r["id"],
                "action_hint": "log_outreach",
            })

        # 4. Calendar conflicts (overlapping events today)
        today_events = conn.execute(
            "SELECT id, title, start_time, end_time FROM calendar_events WHERE start_date = ? AND start_time IS NOT NULL ORDER BY start_time",
            (today,),
        ).fetchall()
        events_list = [dict(e) for e in today_events]
        for i in range(len(events_list) - 1):
            e1 = events_list[i]
            e2 = events_list[i + 1]
            if e1.get("end_time") and e2.get("start_time") and e1["end_time"] > e2["start_time"]:
                items.append({
                    "type": "calendar_conflict",
                    "title": f"Overlap: {e1['title']} & {e2['title']}",
                    "description": f"{e1['start_time']}-{e1['end_time']} overlaps with {e2['start_time']}",
                    "priority": 2,
                    "entity_id": e1["id"],
                    "action_hint": "update_event",
                })

        # 5. Stale goals (no progress update in 14+ days)
        stale_rows = conn.execute(
            "SELECT id, title, progress, updated_at FROM goals WHERE status = 'active' AND updated_at < ? ORDER BY updated_at LIMIT 10",
            (fourteen_days_ago,),
        ).fetchall()
        for r in stale_rows:
            items.append({
                "type": "stale_goal",
                "title": f"Stale goal: {r['title']}",
                "description": f"{r['progress']}% complete, last updated {r['updated_at'][:10]}",
                "priority": 3,
                "entity_id": r["id"],
                "action_hint": "update_goal",
            })

        # 6. Incomplete focus sessions
        incomplete_rows = conn.execute(
            "SELECT id, task_title, started_at, planned_minutes FROM focus_sessions WHERE ended_at IS NULL ORDER BY started_at DESC LIMIT 5",
        ).fetchall()
        for r in incomplete_rows:
            items.append({
                "type": "incomplete_focus",
                "title": f"Open focus session: {r['task_title'] or 'Untitled'}",
                "description": f"Started {r['started_at'][:16]}, planned {r['planned_minutes']} min",
                "priority": 3,
                "entity_id": r["id"],
                "action_hint": "end_focus",
            })

    # Sort by priority (lower number = higher priority)
    items.sort(key=lambda x: x["priority"])
    return items


def get_inbox_count() -> dict:
    """Quick count of inbox items by type."""
    items = get_inbox()
    counts = {}
    for item in items:
        t = item["type"]
        counts[t] = counts.get(t, 0) + 1
    return {"total": len(items), "by_type": counts}
